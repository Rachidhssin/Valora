/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                primary: {
                    50: '#f0f4ff',
                    100: '#e0e8ff',
                    200: '#c7d4fe',
                    300: '#a4b8fc',
                    400: '#818cf8',
                    500: '#667eea',
                    600: '#5a67d8',
                    700: '#4c51bf',
                    800: '#434190',
                    900: '#3c366b',
                },
                secondary: {
                    500: '#764ba2',
                    600: '#6b4190',
                },
                dark: {
                    100: '#1a1a2e',
                    200: '#16213e',
                    300: '#0f0f1a',
                    400: '#0a0a12',
                }
            },
            backgroundImage: {
                'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
                'gradient-primary': 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)',
                'gradient-dark': 'linear-gradient(180deg, #0f0f1a 0%, #1a1a2e 100%)',
            },
            animation: {
                'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'shimmer': 'shimmer 2s linear infinite',
            },
            keyframes: {
                shimmer: {
                    '0%': { backgroundPosition: '-200% 0' },
                    '100%': { backgroundPosition: '200% 0' },
                }
            }
        },
    },
    plugins: [],
}
