export const colors = {
  bg: '#0d1117',
  bgSecondary: '#161b22',
  bgTertiary: '#1c2128',
  border: '#30363d',
  borderHover: '#484f58',
  text: '#c9d1d9',
  textMuted: '#8b949e',
  textBright: '#f0f6fc',
  accent: '#58a6ff',
  accentHover: '#79c0ff',
  green: '#3fb950',
  red: '#f85149',
  orange: '#d29922',
  purple: '#bc8cff',
  cyan: '#39d2c0',
  greenDim: '#238636',
  redDim: '#da3633',
}

export const chartColors = [
  '#58a6ff',
  '#3fb950',
  '#f0883e',
  '#bc8cff',
  '#39d2c0',
  '#f85149',
  '#d29922',
  '#79c0ff',
  '#56d364',
  '#db6d28',
]

export const plotlyLayout = {
  paper_bgcolor: colors.bg,
  plot_bgcolor: colors.bg,
  font: {
    family: "'JetBrains Mono', Consolas, 'Courier New', monospace",
    color: colors.text,
    size: 11,
  },
  margin: { l: 55, r: 20, t: 60, b: 50 },
  xaxis: {
    gridcolor: '#21262d',
    zerolinecolor: '#30363d',
    tickcolor: colors.textMuted,
    linecolor: colors.border,
    automargin: true,
  },
  yaxis: {
    gridcolor: '#21262d',
    zerolinecolor: '#30363d',
    tickcolor: colors.textMuted,
    linecolor: colors.border,
    side: 'right',
    automargin: true,
  },
  legend: {
    bgcolor: 'transparent',
    font: { color: colors.textMuted, size: 10 },
    orientation: 'h',
    yanchor: 'bottom',
    y: 1.02,
    xanchor: 'left',
    x: 0,
  },
  hovermode: 'x unified',
  hoverlabel: {
    bgcolor: colors.bgSecondary,
    bordercolor: colors.border,
    font: { color: colors.text, size: 11, family: 'Consolas, monospace' },
  },
  dragmode: 'zoom',
}

export function truncateLabel(label, maxLen = 18) {
  if (!label || typeof label !== 'string') return label;
  return label.length > maxLen ? label.slice(0, maxLen - 1) + '…' : label;
}

export const plotlyConfig = {
  displayModeBar: true,
  displaylogo: false,
  modeBarButtonsToRemove: ['lasso2d', 'select2d'],
  toImageButtonOptions: {
    format: 'png',
    filename: 'natasha_chart',
    height: 700,
    width: 1400,
    scale: 2,
  },
}
