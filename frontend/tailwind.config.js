/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['"Inter"', '"SF Pro Text"', 'system-ui', 'sans-serif'],
                mono: ['"SF Mono"', '"JetBrains Mono"', 'Menlo', 'monospace'],
            },
            colors: {
                obsidian: '#0a0a0a',
                borderline: '#262626',
                rowhover: '#121212',
                institutional: '#2563EB', // A crisp, legible blue
                success: '#16a34a',
            },
            borderRadius: {
                'precision': '6px',
            },
            typography: {
                DEFAULT: {
                    css: {
                        color: '#a3a3a3',
                        lineHeight: '1.6',
                        h1: { color: '#f5f5f5', fontWeight: '500', letterSpacing: '0.01em' },
                        h2: { color: '#f5f5f5', fontWeight: '500', letterSpacing: '0.01em', marginTop: '2em', marginBottom: '1em' },
                        h3: { color: '#f5f5f5', fontWeight: '500', letterSpacing: '0.01em' },
                        strong: { color: '#f5f5f5', fontWeight: '500' },
                        a: { color: '#2563EB', textDecoration: 'none', '&:hover': { color: '#3b82f6' } },
                        code: { color: '#e5e5e5', backgroundColor: '#171717', padding: '2px 4px', borderRadius: '4px' },
                        li: { marginTop: '0.25em', marginBottom: '0.25em' }
                    },
                },
            },
        },
    },
    plugins: [
        require('@tailwindcss/typography'),
    ],
}
