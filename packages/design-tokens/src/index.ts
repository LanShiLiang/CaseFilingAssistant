/** 跨端仅共享纯数据 token，不共享 DOM 或具体组件实现。 */
export const tokens = {
  color: {
    canvas: "#eef2f0",
    surface: "#ffffff",
    surfaceSoft: "#f5f7f6",
    ink: "#172326",
    muted: "#667477",
    line: "#d8e0dd",
    brand: "#214b4a",
    brandHover: "#173c3b",
    accent: "#ad6d2c",
    success: "#33705b",
    warning: "#9a641f",
    danger: "#a53b3b"
  },
  radius: { sm: 8, md: 12, lg: 18 },
  motion: { feedback: 140, state: 220, flow: 420 },
  space: { xs: 4, sm: 8, md: 16, lg: 24, xl: 32 }
} as const;
