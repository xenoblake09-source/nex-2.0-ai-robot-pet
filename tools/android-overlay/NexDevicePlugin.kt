package ai.nexcompanion.virtualpet

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Base64
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.ImageProxy
import androidx.camera.lifecycle.ProcessCameraProvider
import com.getcapacitor.JSObject
import com.getcapacitor.PermissionState
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import com.getcapacitor.annotation.Permission
import com.getcapacitor.annotation.PermissionCallback
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.face.FaceDetection
import com.google.mlkit.vision.face.FaceDetectorOptions
import java.util.Locale
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * NEX native helper plugin.
 *
 *  - speak / stopSpeaking / isSpeaking : Android TextToSpeech with a real
 *    "speakEnd" event so the web layer knows exactly when to re-arm the mic.
 *  - capturePhoto : single-shot JPEG from the FRONT camera (CameraX).
 *  - startFaceTracking / stopFaceTracking : on-device face presence detection
 *    using ML Kit (the model is bundled, no image ever leaves the device).
 */
@CapacitorPlugin(
    name = "NexDevice",
    permissions = [Permission(strings = [Manifest.permission.CAMERA], alias = "camera")]
)
class NexDevicePlugin : Plugin() {

    companion object {
        private const val CAMERA_ALIAS = "camera"
        private const val UTTERANCE_ID = "nex-utterance"
    }

    private var tts: TextToSpeech? = null
    private var ttsReady = false

    private val executor: ExecutorService = Executors.newSingleThreadExecutor()
    private var imageCapture: ImageCapture? = null
    private var imageAnalysis: ImageAnalysis? = null
    private var cameraProvider: ProcessCameraProvider? = null
    private var faceDetector: com.google.mlkit.vision.face.FaceDetector? = null
    private var lastFacePresent = false

    override fun load() {
        super.load()
        val engine = TextToSpeech(context) { status ->
            ttsReady = status == TextToSpeech.SUCCESS
            if (ttsReady) {
                try {
                    tts?.setLanguage(Locale.getDefault())
                } catch (_: Exception) {
                    // keep the default language
                }
            }
        }
        tts = engine
        engine.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {
                // no-op
            }

            override fun onDone(utteranceId: String?) {
                notifyListeners("speakEnd", JSObject().put("utteranceId", utteranceId ?: UTTERANCE_ID))
            }

            override fun onError(utteranceId: String?) {
                notifyListeners(
                    "speakEnd",
                    JSObject().put("utteranceId", utteranceId ?: UTTERANCE_ID).put("error", true)
                )
            }
        })
    }

    // ------------------------------------------------------------ text to speech

    @PluginMethod
    fun speak(call: PluginCall) {
        val text = call.getString("text") ?: ""
        val lang = call.getString("lang") ?: "en-US"
        val rate = call.getFloat("rate") ?: 1.0f
        val pitch = call.getFloat("pitch") ?: 1.0f

        if (text.isBlank()) {
            call.resolve(JSObject().put("queued", false))
            return
        }

        val engine = tts
        if (engine == null || !ttsReady) {
            call.reject("Text-to-speech engine is not ready.", "TTS_NOT_READY")
            return
        }

        try {
            val locale = Locale.forLanguageTag(lang)
            val result = engine.setLanguage(locale)
            if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                engine.setLanguage(Locale.US)
            }
            engine.setSpeechRate(rate)
            engine.setPitch(pitch)
            engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, UTTERANCE_ID)
            call.resolve(JSObject().put("queued", true))
        } catch (error: Exception) {
            call.reject("Text-to-speech failed: ${error.message}", "TTS_ERROR")
        }
    }

    @PluginMethod
    fun stopSpeaking(call: PluginCall) {
        try {
            tts?.stop()
        } catch (_: Exception) {
            // ignore
        }
        call.resolve()
    }

    @PluginMethod
    fun isSpeaking(call: PluginCall) {
        val speaking = try {
            tts?.isSpeaking == true
        } catch (_: Exception) {
            false
        }
        call.resolve(JSObject().put("speaking", speaking))
    }

    // ----------------------------------------------------------------- camera

    @PluginMethod
    fun hasCamera(call: PluginCall) {
        val pm = context.packageManager
        val available = pm.hasSystemFeature(PackageManager.FEATURE_CAMERA_ANY) ||
            pm.hasSystemFeature(PackageManager.FEATURE_CAMERA_FRONT)
        call.resolve(JSObject().put("available", available))
    }

    @PluginMethod
    fun requestCameraPermission(call: PluginCall) {
        if (getPermissionState(CAMERA_ALIAS) == PermissionState.GRANTED) {
            call.resolve(JSObject().put("granted", true))
            return
        }
        requestPermissionForAlias(CAMERA_ALIAS, call, "cameraPermissionCallback")
    }

    @PermissionCallback
    private fun cameraPermissionCallback(call: PluginCall) {
        val granted = getPermissionState(CAMERA_ALIAS) == PermissionState.GRANTED
        call.resolve(JSObject().put("granted", granted))
    }

    @PluginMethod
    fun capturePhoto(call: PluginCall) {
        val activity = activity
        if (activity == null) {
            call.reject("No activity available.", "CAMERA_ERROR")
            return
        }
        if (getPermissionState(CAMERA_ALIAS) != PermissionState.GRANTED) {
            call.reject("Camera permission is not granted.", "PERMISSION_DENIED")
            return
        }

        executor.execute {
            var provider: ProcessCameraProvider? = null
            try {
                provider = obtainCameraProvider(activity)
                val capture = ImageCapture.Builder()
                    .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                    .build()
                imageCapture = capture

                provider.unbindAll()
                provider.bindToLifecycle(activity, CameraSelector.DEFAULT_FRONT_CAMERA, capture)

                capture.takePicture(
                    executor,
                    object : ImageCapture.OnImageCapturedCallback() {
                        override fun onCaptureSuccess(image: ImageProxy) {
                            val bytes = readJpegBytes(image)
                            image.close()
                            val encoded = Base64.encodeToString(bytes, Base64.NO_WRAP)
                            call.resolve(
                                JSObject()
                                    .put("base64", encoded)
                                    .put("mimeType", "image/jpeg")
                                    .put("bytes", bytes.size)
                            )
                            try {
                                provider?.unbindAll()
                            } catch (_: Exception) {
                                // ignore
                            }
                        }

                        override fun onError(exception: ImageCaptureException) {
                            call.reject(
                                "Camera capture failed: ${exception.message}",
                                "CAMERA_ERROR"
                            )
                            try {
                                provider?.unbindAll()
                            } catch (_: Exception) {
                                // ignore
                            }
                        }
                    }
                )
            } catch (error: Exception) {
                call.reject("Camera is unavailable: ${error.message}", "CAMERA_ERROR")
            }
        }
    }

    // ---------------------------------------------------------- face tracking

    @PluginMethod
    fun startFaceTracking(call: PluginCall) {
        val activity = activity
        if (activity == null) {
            call.reject("No activity available.", "CAMERA_ERROR")
            return
        }
        if (getPermissionState(CAMERA_ALIAS) != PermissionState.GRANTED) {
            call.reject("Camera permission is not granted.", "PERMISSION_DENIED")
            return
        }

        executor.execute {
            try {
                val provider = obtainCameraProvider(activity)
                cameraProvider = provider

                val options = FaceDetectorOptions.Builder()
                    .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_FAST)
                    .setLandmarkMode(FaceDetectorOptions.LANDMARK_MODE_NONE)
                    .setClassificationMode(FaceDetectorOptions.CLASSIFICATION_MODE_NONE)
                    .setMinFaceSize(0.15f)
                    .build()

                val detector = FaceDetection.getClient(options)
                faceDetector = detector

                val analysis = ImageAnalysis.Builder()
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .build()
                imageAnalysis = analysis

                analysis.setAnalyzer(executor) { imageProxy ->
                    val mediaImage = imageProxy.image
                    if (mediaImage == null) {
                        imageProxy.close()
                    } else {
                        val image = InputImage.fromMediaImage(
                            mediaImage,
                            imageProxy.imageInfo.rotationDegrees
                        )
                        detector.process(image)
                            .addOnSuccessListener { faces ->
                                val present = faces.isNotEmpty()
                                if (present != lastFacePresent) {
                                    lastFacePresent = present
                                    notifyListeners(
                                        "faceStatus",
                                        JSObject().put("present", present).put("count", faces.size)
                                    )
                                }
                            }
                            .addOnCompleteListener { imageProxy.close() }
                    }
                }

                provider.unbindAll()
                provider.bindToLifecycle(activity, CameraSelector.DEFAULT_FRONT_CAMERA, analysis)
                call.resolve(JSObject().put("started", true))
            } catch (error: Exception) {
                call.reject("Face tracking failed: ${error.message}", "CAMERA_ERROR")
            }
        }
    }

    @PluginMethod
    fun stopFaceTracking(call: PluginCall) {
        try {
            imageAnalysis?.clearAnalyzer()
            cameraProvider?.unbindAll()
            imageAnalysis = null
            faceDetector?.close()
            faceDetector = null
        } catch (_: Exception) {
            // ignore
        }
        call.resolve()
    }

    // ------------------------------------------------------------------ utils

    private fun obtainCameraProvider(activity: Activity): ProcessCameraProvider {
        val future = ProcessCameraProvider.getInstance(activity)
        return future.get(10, TimeUnit.SECONDS)
    }

    /** Copies the compressed JPEG bytes out of a captured [ImageProxy]. */
    private fun readJpegBytes(image: ImageProxy): ByteArray {
        val plane = image.planes.firstOrNull() ?: return ByteArray(0)
        val buffer = plane.buffer
        val bytes = ByteArray(buffer.remaining())
        buffer.get(bytes)
        return bytes
    }

    override fun handleOnDestroy() {
        try {
            imageAnalysis?.clearAnalyzer()
            cameraProvider?.unbindAll()
            faceDetector?.close()
            tts?.stop()
            tts?.shutdown()
            executor.shutdownNow()
        } catch (_: Exception) {
            // ignore
        }
        super.handleOnDestroy()
    }
}
