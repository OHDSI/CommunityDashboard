const path = require('path');
module.exports = {
  "stories": [
    "../projects/**/*.mdx",
    "../projects/**/*.stories.@(js|jsx|ts|tsx)"
  ],
  "addons": [
    "@storybook/addon-links",
    "@storybook/addon-essentials",
    "@storybook/addon-interactions"
  ],
  "framework": {
    "name": "@storybook/angular",
    "options": {}
  },
  "docs": {
    "autodocs": "tag"
  }
}