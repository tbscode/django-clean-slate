const path = require('path');
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');
const CompressionPlugin = require('compression-webpack-plugin');
var config = function (env) {
  var publicPath = '/static/dist/example_app/';
  var devTool = env.DEV_TOOL;
  //var outputPath = './dist/example_app';
  // It is always assumed that the backend is mounted at /back
  var outputPath = '../back/static/dist/example_app';
  var entryPoint = './apps/example_app/src/index.js';
  var debug = env.DEBUG === '1';

  return {
    context: __dirname,
    entry: {
      staticfiles: entryPoint,
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'apps/example_app/src/'),
        '@django': path.resolve(__dirname, '../back/static/'),
      },
    },
    output: {
      path: path.join(__dirname, outputPath),
      filename: '[name]-[hash].js',
      publicPath: publicPath,
    },

    plugins: [
      new BundleTracker({
        filename: path.join(
          __dirname,
          './example_app.webpack-stats.json'
        ),
      }),
      new CompressionPlugin(),
    ],
    devtool: devTool,
    module: {
      rules: [
        {
          test: /\.(js|jsx|tsx|ts)$/,
          exclude: /node_modules/,
          use: ['babel-loader'],
          resolve: {
            extensions: ['.js', '.jsx'],
          },
          include: [path.resolve(__dirname, 'apps/example_app/src')],
        },
        {
          test: /\.svg$/,
          issuer: /\.jsx?$/,
          use: [
            'babel-loader',
            {
              loader: 'react-svg-loader',
              options: {
                svgo: {
                  plugins: [{ removeTitle: false }],
                  floatPrecision: 2,
                },
                jsx: true,
              },
            },
          ],
        },
        {
          test: /\.(ttf)$/,
          use: {
            loader: 'file-loader',
            options: {
              name: '[name].[hash:8].[ext]',
            },
          },
        },
        {
          test: /\.css$/,
          use: ['style-loader', 'css-loader'],
        },
        {
          test: /\.(png|jpg|gif)$/,
          use: ['file-loader'],
        },
      ],
    },
  };
};

module.exports = (env, argv) => {
  const conf = config(env);
  console.log(conf);
  return conf;
};
