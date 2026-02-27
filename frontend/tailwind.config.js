/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f4ff',
          100: '#dce6ff',
          200: '#bdd0ff',
          300: '#90afff',
          400: '#5d85ff',
          500: '#3b62f5',
          600: '#2340e8',
          700: '#1b31d0',
          800: '#1c2aa8',
          900: '#1e2b84',
          950: '#141a52',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
