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
  entry: "./modules/map.js",
  output: {
    filename: "map-bundle.js",
    path: path.resolve("../ottm/static/ottm/map"),
  },
};
