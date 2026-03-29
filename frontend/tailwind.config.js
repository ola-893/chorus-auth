/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        headline: ['"Space Grotesk"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        body: ['"Manrope"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        background: '#131313',
        surface: '#131313',
        'surface-container': '#1f1f1f',
        'surface-container-low': '#1b1b1b',
        'surface-container-lowest': '#0e0e0e',
        'surface-container-high': '#2a2a2a',
        'on-background': '#e2e2e2',
        'on-surface': '#e2e2e2',
        'on-surface-variant': '#c6c6c6',
        'outline-variant': '#474747',
        primary: '#ffffff',
        'on-primary': '#1a1c1c',
      },
    },
  },
  plugins: [],
};
