export type ExpressionName =
  | 'neutral'
  | 'happy'
  | 'sad'
  | 'angry'
  | 'sleep'
  | 'blink'
  | 'dance'
  | 'surprised'
  | 'thinking'
  | 'listening'
  | 'speaking'
  | 'laugh'
  | 'cry'
  | 'love'
  | 'gaming'
  | 'curious'
  | 'confused'
  | 'excited';

export type ActionType =
  | 'none'
  | 'animal_sound'
  | 'dance'
  | 'tell_time'
  | 'tell_date'
  | 'joke'
  | 'riddle'
  | 'game'
  | 'weather'
  | 'school'
  | 'sleep'
  | 'wake';

export interface ChatAction {
  type: ActionType;
  animal?: string | null;
  payload?: Record<string, unknown> | null;
}

export interface ChatReply {
  reply: string;
  expression: ExpressionName;
  action: ChatAction;
  language: string;
  source: string;
  model?: string | null;
  latency_ms?: number;
  school_used?: boolean;
  creator_intro?: boolean;
}

export interface VisionReply {
  reply: string;
  expression: ExpressionName;
  object_name?: string | null;
  face_present?: boolean | null;
  model?: string | null;
  latency_ms?: number;
  language?: string;
}

export interface ConversationTurn {
  role: 'user' | 'nex';
  content: string;
}

export type NexStatus =
  | 'boot'
  | 'idle'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'playing_sound'
  | 'error';

export type ErrorKind = 'network' | 'backend' | 'gemini' | 'permission' | 'unknown';

export class NexApiError extends Error {
  kind: ErrorKind;
  code: string;
  status?: number;

  constructor(message: string, kind: ErrorKind, code = 'unknown', status?: number) {
    super(message);
    this.name = 'NexApiError';
    this.kind = kind;
    this.code = code;
    this.status = status;
  }
}
