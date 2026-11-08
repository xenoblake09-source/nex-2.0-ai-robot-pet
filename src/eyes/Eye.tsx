import { useEffect, useRef } from 'react';
import { eyeEngine, type EyeDraw } from './engine';

interface EyeProps {
  index: 0 | 1;
}

/**
 * One expressive robot eye.
 *
 * The component renders the SVG once; the engine then writes attributes
 * directly on the nodes every frame (no React re-render, no layout thrash).
 */
export default function Eye({ index }: EyeProps) {
  const rootRef = useRef<SVGGElement>(null);
  const bodyRef = useRef<SVGPathElement>(null);
  const bodyShadeRef = useRef<SVGPathElement>(null);
  const clipRef = useRef<SVGPathElement>(null);
  const haloRef = useRef<SVGPathElement>(null);
  const pupilRef = useRef<SVGPathElement>(null);
  const heartRef = useRef<SVGPathElement>(null);
  const tearRef = useRef<SVGPathElement>(null);
  const hl1Ref = useRef<SVGCircleElement>(null);
  const hl2Ref = useRef<SVGCircleElement>(null);
  const glowStopRef = useRef<SVGStopElement>(null);
  const glowStop2Ref = useRef<SVGStopElement>(null);

  useEffect(() => {
    const apply = (draw: EyeDraw) => {
      const root = rootRef.current;
      if (!root) return;
      root.setAttribute(
        'transform',
        `translate(${draw.translateX.toFixed(2)} ${draw.translateY.toFixed(2)}) ` +
          `rotate(${draw.rotate.toFixed(2)} 120 120) ` +
          `translate(120 120) scale(${draw.scale.toFixed(3)}) translate(-120 -120)`,
      );

      bodyRef.current?.setAttribute('d', draw.bodyPath);
      bodyRef.current?.setAttribute('fill', draw.tint);
      bodyRef.current?.setAttribute('stroke', draw.glow);
      bodyRef.current?.setAttribute('stroke-opacity', draw.strokeOpacity.toFixed(3));

      bodyShadeRef.current?.setAttribute('d', draw.bodyPath);
      clipRef.current?.setAttribute('d', draw.bodyPath);

      haloRef.current?.setAttribute('d', draw.haloPath);
      haloRef.current?.setAttribute('opacity', draw.haloOpacity.toFixed(3));
      glowStopRef.current?.setAttribute('stop-color', draw.glow);
      glowStop2Ref.current?.setAttribute('stop-color', draw.glow);

      pupilRef.current?.setAttribute('d', draw.pupilPath);
      pupilRef.current?.setAttribute('fill', draw.pupilColor);
      pupilRef.current?.setAttribute('opacity', draw.pupilOpacity.toFixed(3));

      heartRef.current?.setAttribute('d', draw.heartPath);
      heartRef.current?.setAttribute('opacity', draw.heartOpacity.toFixed(3));

      tearRef.current?.setAttribute('d', draw.tearPath);
      tearRef.current?.setAttribute('opacity', draw.tearOpacity.toFixed(3));

      if (hl1Ref.current) {
        hl1Ref.current.setAttribute('cx', (draw.pupilCx - draw.pupilRadius * 0.34).toFixed(2));
        hl1Ref.current.setAttribute('cy', (draw.pupilCy - draw.pupilRadius * 0.38).toFixed(2));
        hl1Ref.current.setAttribute('r', (draw.pupilRadius * 0.22).toFixed(2));
        hl1Ref.current.setAttribute('opacity', draw.highlightOpacity.toFixed(3));
      }
      if (hl2Ref.current) {
        hl2Ref.current.setAttribute('cx', (draw.pupilCx + draw.pupilRadius * 0.34).toFixed(2));
        hl2Ref.current.setAttribute('cy', (draw.pupilCy + draw.pupilRadius * 0.38).toFixed(2));
        hl2Ref.current.setAttribute('r', (draw.pupilRadius * 0.12).toFixed(2));
        hl2Ref.current.setAttribute('opacity', (draw.highlightOpacity * 0.7).toFixed(3));
      }
    };

    eyeEngine.register(index, apply);
    return () => eyeEngine.unregister(index);
  }, [index]);

  const uid = `eye${index}`;

  return (
    <svg
      className="nex-eye"
      viewBox="0 0 240 240"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <radialGradient id={`${uid}-halo`} cx="50%" cy="50%" r="50%">
          <stop ref={glowStopRef} offset="45%" stopColor="#3FD8FF" stopOpacity="0.5" />
          <stop ref={glowStop2Ref} offset="100%" stopColor="#3FD8FF" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={`${uid}-shade`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.18" />
          <stop offset="45%" stopColor="#ffffff" stopOpacity="0" />
          <stop offset="100%" stopColor="#0b1b2a" stopOpacity="0.22" />
        </linearGradient>
        <clipPath id={`${uid}-clip`}>
          <path ref={clipRef} d="" />
        </clipPath>
      </defs>

      <g ref={rootRef}>
        <path
          ref={haloRef}
          fill={`url(#${uid}-halo)`}
          opacity="0"
          transform="translate(120 120) scale(1.22) translate(-120 -120)"
          style={{ filter: 'blur(6px)' }}
        />
        <path ref={bodyRef} d="" strokeWidth="2.2" strokeLinejoin="round" />
        <path ref={bodyShadeRef} d="" fill={`url(#${uid}-shade)`} />

        <g clipPath={`url(#${uid}-clip)`}>
          <path ref={pupilRef} d="" />
          <path ref={heartRef} d="" fill="#FF2E74" />
          <circle ref={hl1Ref} cx="0" cy="0" r="0" fill="#ffffff" />
          <circle ref={hl2Ref} cx="0" cy="0" r="0" fill="#ffffff" opacity="0.7" />
          <path ref={tearRef} d="" fill="#7FD8FF" opacity="0" />
        </g>
      </g>
    </svg>
  );
}
