/** @type {import('tailwindcss').Config} */
const withMT = require("@material-tailwind/html/utils/withMT");

module.exports = withMT ({
  content: ["./templates/*"],
  theme: {
    extend: {
    },
  },
  plugins: [require("daisyui"),require("tailgrids/plugin")],
});