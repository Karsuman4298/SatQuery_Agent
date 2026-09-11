// Animation state machine types for SatQuery AI Phase 1

export type AnimationPhase =
  | 'INTRO'
  | 'FORMING_PAGE'
  | 'EARTH_FORMING'
  | 'BRANDING_FORMING'
  | 'ENTRY_READY'
  | 'EARTH_HOVER'
  | 'EARTH_ENTERING'
  | 'PAGE_DISSOLVING'
  | 'AUTH_TRANSITION_READY';

export interface Particle {
  id: number;
  x: number;
  y: number;
  targetX: number;
  targetY: number;
  startX: number;
  startY: number;
  r: number;
  g: number;
  b: number;
  alpha: number;
  targetAlpha: number;
  size: number;
  targetSize: number;
  progress: number;
  speed: number;
  layer: ParticleLayer;
  active: boolean;
  dissolving: boolean;
  dissolveVx: number;
  dissolveVy: number;
}

export type ParticleLayer =
  | 'space'
  | 'stars'
  | 'satellite'
  | 'earth'
  | 'atmosphere'
  | 'citylights'
  | 'brand'
  | 'headline'
  | 'subtext';

export interface EarthTextureData {
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  width: number;
  height: number;
}
