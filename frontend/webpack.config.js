const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');

module.exports = {
  entry: './src/index.tsx',  // Our project starts by running this script file
  output: {
    path: path.resolve(__dirname, 'static'),  // where to save all the compiled files
    filename: 'js/bundle.js',  // where to save the project script
  },
  resolve: {
    extensions: ['.tsx', '.ts', '.js'],
    // Path Mapping (allows imports relative to the frontend src and static directories)
    alias: {
      '@/static': path.resolve(__dirname, 'static'),
      '@': path.resolve(__dirname, 'src'),
    },
  },
  module: {
    rules: [
      {
        // Compile our scripts to our output dir under js/
        test: /\.tsx?$/,
        use: 'ts-loader',
        exclude: /node_modules/,
      },
      {
        // Compile our styles to our output dir under css/
        test: /\.scss$/,
        use: [
          MiniCssExtractPlugin.loader,
          'css-loader',
          {
            loader: 'postcss-loader',
            options: {
              postcssOptions: {
                plugins: [
                  // Add vendor prefixes to CSS rules using values from Can-I-Use. (for better compatibility)
                  ['autoprefixer'],
                ],
              },
            },
          },
          'sass-loader',
        ],
      },
      {
        // Copy the used files from static/ to our output directory
        test: /\.(png|jpe?g|gif|svg|ico|ttf|otf|woff|mp3|ogg|wav)$/i,
        loader: 'file-loader',
        options: {
          context: path.resolve(__dirname, 'static'),
          name: '[path][name].[ext]',
        },
      },
    ],
  },
  plugins: [
    // Define the css minimization plugin with its options
    new MiniCssExtractPlugin({
      filename: "css/[name].css", // Output main CSS files to a 'css' directory with file name
      chunkFilename: "css/[id].[contenthash].css", // Output chunk CSS files content hash
    }),
  ],
};
