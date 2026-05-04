/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        canvas: {
          bg: '#0f0f0f',
          surface: '#1a1a1a',
          border: '#2a2a2a',
          hover: '#333333',
          accent: '#6366f1',
          'accent-hover': '#4f46e5',
          danger: '#ef4444',
          success: '#22c55e',
          warning: '#f59e0b',
          text: '#e5e5e5',
          'text-muted': '#999999',
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
};