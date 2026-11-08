/**
 * NEX eye expressions.
 *
 * Every expression is a set of continuous parameters for one eye. The engine
 * interpolates between them so transitions are smooth and never pop.
 *
 * Units:
 *   topInset / bottomInset  0..1 fraction of the eye height covered by a lid
 *   tilt                   -1..1 rotation of the eye opening
 *   pupilScale             0..1 size of the pupil
 *   pupilX / pupilY        -1..1 position of the pupil inside the eye
 *   pupilExponent          2 = ellipse, 8 = rounded square
 *   heart                  0..1 blend of a heart-shaped pupil
 *   tear                   0..1 opacity of the tears
 */

export interface EyeState {
  topInset: number;
  bottomInset: number;
  tilt: number;
  pupilScale: number;
  pupilX: number;
  pupilY: number;
  pupilExponent: number;
  heart: number;
  tear: number;
  tint: string;
  glow: string;
  pupilColor: string;
  halo: number;
}

export type Behavior =
  | 'idle'
  | 'talk'
  | 'dance'
  | 'think'
  | 'sleep'
  | 'game'
  | 'lookAround'
  | 'happyBounce';

export interface ExpressionPreset {
  /** Shared parameters for both eyes. */
  base: Partial<EyeState>;
  /** Overrides for the left eye. */
  eye0?: Partial<EyeState>;
  /** Overrides for the right eye. */
  eye1?: Partial<EyeState>;
  /** Mirror `tilt` on the right eye (keeps angry/sad faces symmetric). */
  mirrorTilt?: boolean;
  behavior?: Behavior;
}

export const DEFAULT_EYE: EyeState = {
  topInset: 0.05,
  bottomInset: 0.05,
  tilt: 0,
  pupilScale: 0.5,
  pupilX: 0,
  pupilY: 0,
  pupilExponent: 3.0,
  heart: 0,
  tear: 0,
  tint: '#F0FAFF',
  glow: '#3FD8FF',
  pupilColor: '#0B1B2A',
  halo: 0.55,
};

export const EXPRESSIONS: Record<string, ExpressionPreset> = {
  neutral: {
    base: {},
    behavior: 'lookAround',
  },

  happy: {
    base: {
      topInset: 0.17,
      bottomInset: 0.09,
      pupilScale: 0.52,
      pupilExponent: 2.8,
      glow: '#57E7FF',
      halo: 0.8,
    },
    behavior: 'happyBounce',
  },

  sad: {
    base: {
      topInset: 0.06,
      bottomInset: 0.24,
      tilt: -0.34,
      pupilScale: 0.56,
      pupilY: 0.22,
      glow: '#7FA8FF',
      tint: '#EDF2FF',
      halo: 0.4,
      tear: 0.45,
    },
    behavior: 'idle',
  },

  angry: {
    base: {
      topInset: 0.3,
      bottomInset: 0.04,
      tilt: 0.5,
      pupilScale: 0.42,
      pupilExponent: 4.5,
      glow: '#FF5A5A',
      tint: '#FFE9E9',
      pupilColor: '#2A0808',
      halo: 0.7,
    },
    behavior: 'idle',
  },

  sleep: {
    base: {
      topInset: 0.46,
      bottomInset: 0.46,
      pupilScale: 0.12,
      glow: '#6E86FF',
      tint: '#E8ECFF',
      halo: 0.3,
    },
    behavior: 'sleep',
  },

  blink: {
    base: {
      topInset: 0.44,
      bottomInset: 0.44,
      pupilScale: 0.3,
    },
    behavior: 'idle',
  },

  dance: {
    base: {
      topInset: 0.12,
      bottomInset: 0.12,
      pupilScale: 0.46,
      pupilExponent: 4,
      glow: '#FF7AE0',
      halo: 0.95,
    },
    behavior: 'dance',
  },

  surprised: {
    base: {
      topInset: 0,
      bottomInset: 0,
      pupilScale: 0.22,
      pupilExponent: 2,
      glow: '#B9F5FF',
      tint: '#FFFFFF',
      halo: 1,
    },
    behavior: 'idle',
  },

  thinking: {
    base: {
      topInset: 0.11,
      pupilScale: 0.44,
      pupilExponent: 2.8,
      glow: '#9AD8FF',
      halo: 0.6,
    },
    behavior: 'think',
  },

  listening: {
    base: {
      topInset: 0.01,
      pupilScale: 0.66,
      pupilExponent: 2,
      glow: '#6BFFB8',
      halo: 0.85,
    },
    behavior: 'idle',
  },

  speaking: {
    base: {
      topInset: 0.05,
      pupilScale: 0.5,
      pupilExponent: 3.0,
      glow: '#5FE0FF',
      halo: 0.75,
    },
    behavior: 'talk',
  },

  laugh: {
    base: {
      topInset: 0.36,
      bottomInset: 0.2,
      pupilScale: 0.3,
      glow: '#FFD166',
      tint: '#FFF8E6',
      halo: 0.9,
    },
    behavior: 'happyBounce',
  },

  cry: {
    base: {
      topInset: 0.14,
      bottomInset: 0.32,
      pupilScale: 0.4,
      glow: '#8FB8FF',
      tint: '#EDF2FF',
      halo: 0.35,
      tear: 1,
    },
    behavior: 'idle',
  },

  love: {
    base: {
      topInset: 0.08,
      bottomInset: 0.08,
      pupilScale: 0.72,
      pupilExponent: 2.8,
      heart: 1,
      glow: '#FF5FA2',
      tint: '#FFECF4',
      pupilColor: '#FF2E74',
      halo: 1,
    },
    behavior: 'happyBounce',
  },

  gaming: {
    base: {
      topInset: 0.02,
      bottomInset: 0.02,
      pupilScale: 0.58,
      pupilExponent: 7,
      glow: '#39FF88',
      tint: '#E9FFF1',
      pupilColor: '#04220F',
      halo: 0.9,
    },
    behavior: 'game',
  },

  curious: {
    base: {
      topInset: 0.04,
      pupilScale: 0.46,
      pupilX: 0.28,
      pupilY: -0.22,
      pupilExponent: 2.8,
      glow: '#7FD6FF',
      halo: 0.7,
    },
    eye0: { topInset: 0.0, pupilX: 0.36, pupilY: -0.3 },
    eye1: { topInset: 0.12, pupilX: 0.16, pupilY: -0.08 },
    behavior: 'idle',
  },

  confused: {
    base: {
      topInset: 0.1,
      pupilScale: 0.44,
      pupilExponent: 2.8,
      glow: '#FFC14D',
      halo: 0.65,
    },
    eye0: { topInset: 0.24, pupilX: -0.42, pupilY: 0.08 },
    eye1: { topInset: 0.02, pupilX: 0.4, pupilY: -0.12 },
    behavior: 'idle',
  },

  excited: {
    base: {
      topInset: 0,
      bottomInset: 0,
      pupilScale: 0.44,
      pupilExponent: 2.8,
      glow: '#FF9DE2',
      halo: 1,
    },
    behavior: 'happyBounce',
  },
};

/** Expressions used to signal a failure to the user. */
export const ERROR_EXPRESSIONS: Record<string, string> = {
  network: 'sad',
  backend: 'confused',
  gemini: 'confused',
  permission: 'angry',
  unknown: 'confused',
};
