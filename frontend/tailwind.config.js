export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: '#2AABEE', dark: '#1e9ed6' },
        surface: { 1: '#0f1828', 2: '#111b2e', 3: '#141c2e', hover: '#172035', sel: '#1c2a45' },
      },
    },
  },
  plugins: [],
}
