import { defineConfig } from 'vitepress'

export default defineConfig({
  // リポジトリ名
  base: '/knowledge-forge/', 
  title: "Knowledge Forge",
  description: "Engineering Best Practices",
  themeConfig: {
    nav: [
      { text: 'Home', link: '/' },
      { text: 'API Design', link: '/api-design/' },
      { text: 'DB Design', link: '/database-design/' }
    ],
    sidebar: [
      {
        text: 'API Design',
        items: [
          { text: 'Overview', link: '/api-design/overview' }
        ]
      }
    ],
    socialLinks: [
      { icon: 'github', link: 'https://github.com/disalice/knowledge-forge' }
    ]
  }
})