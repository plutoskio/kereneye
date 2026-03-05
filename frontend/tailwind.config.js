/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            typography: {
                DEFAULT: {
                    css: {
                        color: '#cbd5e1',
                        h1: { color: '#f8fafc' },
                        h2: { color: '#f8fafc' },
                        h3: { color: '#f8fafc' },
                        strong: { color: '#f8fafc' },
                        a: { color: '#8b5cf6', '&:hover': { color: '#a78bfa' } },
                        code: { color: '#818cf8' },
                    },
                },
            },
        },
    },
    plugins: [
        require('@tailwindcss/typography'),
    ],
}
