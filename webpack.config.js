// noinspection NodeCoreCodingAssistance
const path = require("path");

module.exports = {
  module: {
    rules: [
      {
        test: /\.css$/,
        use: ["style-loader", "css-loader"]
      }
    ]
  },
  entry: "./js_modules/map.js",
  output: {
    filename: "map-bundle.js",
    path: path.resolve(__dirname, "./ottm/static/ottm/map"),
  },
};
