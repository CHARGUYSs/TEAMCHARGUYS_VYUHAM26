/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        sky: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          500: '#0ea5e9',
          700: '#0369a1',
        },
        teal: {
          400: '#2dd4bf',
          500: '#14b8a6',
        },
      },
      boxShadow: {
        soft: '0 20px 45px rgba(14, 165, 233, 0.12)',
      },
    },
  },
  plugins: [],
};
