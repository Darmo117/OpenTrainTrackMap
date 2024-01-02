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
  entry: "./modules/index-default.ts",
  devtool: "inline-source-map",
  output: {
    filename: "index-bundle.js",
    path: path.resolve("../ottm/static/ottm"),
  },
};
