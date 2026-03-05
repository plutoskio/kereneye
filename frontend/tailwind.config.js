/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['"Inter"', 'system-ui', 'sans-serif'],
            },
            colors: {
                background: '#F9FAFB', // Off-white/slate-50
                surface: '#FFFFFF', // Pure white cards
                primary: {
                    50: '#eff6ff',
                    100: '#dbeafe',
                    500: '#3b82f6', // Friendly blue
                    600: '#2563eb',
                    700: '#1d4ed8',
                },
                text: {
                    main: '#1F2937', // Gray-800
                    muted: '#6B7280', // Gray-500
                    soft: '#9CA3AF', // Gray-400
                },
                borderline: '#E5E7EB', // Gray-200
            },
            borderRadius: {
                'friendly': '20px',
                'super': '28px',
            },
            boxShadow: {
                'soft': '0 4px 20px -2px rgba(0, 0, 0, 0.05)',
                'float': '0 8px 30px -4px rgba(0, 0, 0, 0.08)',
            },
            typography: {
                DEFAULT: {
                    css: {
                        color: '#374151',
                        lineHeight: '1.75',
                        h1: { color: '#111827', fontWeight: '700' },
                        h2: { color: '#1F2937', fontWeight: '600', marginTop: '1.5em', marginBottom: '0.75em' },
                        h3: { color: '#374151', fontWeight: '600' },
                        strong: { color: '#111827', fontWeight: '600' },
                        a: { color: '#3b82f6', textDecoration: 'none', fontWeight: '500', '&:hover': { color: '#2563eb' } },
                        code: { color: '#1f2937', backgroundColor: '#f3f4f6', padding: '2px 6px', borderRadius: '6px', fontWeight: '500' },
                        blockquote: { borderLeftColor: '#3b82f6', color: '#4b5563', fontStyle: 'normal' },
                        ul: { marginTop: '0.5em', marginBottom: '0.5em' },
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
