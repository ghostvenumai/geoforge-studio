/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#111827',
        canvas: '#f4f6f8',
        brand: { 50: '#eefbf8', 100: '#d6f5ed', 500: '#159a85', 600: '#0f7c6d', 700: '#106359' },
      },
      boxShadow: { panel: '0 1px 2px rgba(15,23,42,.06), 0 8px 32px rgba(15,23,42,.05)' },
      fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'] },
    },
  },
  plugins: [],
}
