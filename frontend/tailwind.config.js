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
                display: ['"Inter"', '"SF Pro Display"', 'system-ui', 'sans-serif'], // For headers
            },
            colors: {
                altruistDark: '#000000',
                altruistWhite: '#FFFFFF',
                altruistGray: {
                    50: '#F9FAFB',
                    100: '#F3F4F6',
                    200: '#E5E7EB',
                    300: '#D1D5DB',
                    400: '#9CA3AF',
                    500: '#6B7280',
                    800: '#1F2937',
                    900: '#111827',
                },
                altruistBlue: '#1565C0', // Strong, high-contrast blue for charts/accents
            },
            borderRadius: {
                'sm': '4px',
                'md': '6px',
                'lg': '8px',
            },
            typography: {
                DEFAULT: {
                    css: {
                        color: '#111827',
                        lineHeight: '1.6',
                        h1: { color: '#000000', fontWeight: '600', letterSpacing: '-0.02em', fontFamily: '"Inter", sans-serif' },
                        h2: { color: '#000000', fontWeight: '600', letterSpacing: '-0.01em', marginTop: '2em', marginBottom: '1em' },
                        h3: { color: '#111827', fontWeight: '500' },
                        strong: { color: '#000000', fontWeight: '600' },
                        a: { color: '#1565C0', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } },
                        code: { color: '#111827', backgroundColor: '#F3F4F6', padding: '2px 4px', borderRadius: '4px', fontWeight: '500' },
                        li: { marginTop: '0.25em', marginBottom: '0.25em' },
                        p: { color: '#374151', fontSize: '15px' }
                    },
                },
            },
        },
    },
    plugins: [
        require('@tailwindcss/typography'),
    ],
}
