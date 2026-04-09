/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
    './pages/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#7c3aed',
        accent: '#06b6d4',
      },
      keyframes: {
        float: {
          '0%,100%': { transform: 'translateY(-4px)' },
          '50%': { transform: 'translateY(4px)' },
        },
      },
      animation: {
        float: 'float 6s ease-in-out infinite',
      },
      backdropBlur: {
        sm: '4px',
        md: '8px',
      }
    },
  },
  plugins: [],
}
