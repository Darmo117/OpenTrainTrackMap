// noinspection NodeCoreCodingAssistance
const path = require("path");

module.exports = {
  module: {
    rules: [
      {
        test: /\.css$/,
        use: ["style-loader", "css-loader"]
      },
      {
        test: /\.tsx?$/,
        use: "ts-loader",
        exclude: /node_modules/,
      },
    ]
  },
  resolve: {
    extensions: [".tsx", ".ts", ".js"],
  },
  entry: "./modules/index-wiki.ts",
  devtool: "inline-source-map",
  output: {
    filename: "index-bundle.js",
    path: path.resolve("../ottm/static/ottm/wiki"),
  },
};
