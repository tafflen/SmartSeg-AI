/** Intentional SmartSeg palette: forest green + cream + terracotta reflect the
 * physical waste journey; functional category colours are kept distinct. */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        forest: '#1F3D2B', moss: '#426B4F', cream: '#F7F5EF', paper: '#FFFDF8',
        terracotta: '#C9793A', clay: '#A85634', ink: '#26322B', line: '#D8D4C8',
        plastic: '#3A7CA5', organic: '#4F8A5B', metal: '#7A7F85', other: '#D49A29',
      },
      fontFamily: { display: ['Fraunces', 'serif'], body: ['Work Sans', 'sans-serif'] },
      boxShadow: { paper: '0 7px 24px rgba(31, 61, 43, .08)' },
    },
  },
  plugins: [],
}
