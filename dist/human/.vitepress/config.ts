import { defineConfig } from 'vitepress'

export default defineConfig({
  // リポジトリ名
  base: '/documents/', 
  title: "Knowledge Repository",
  description: "Engineering Best Practices & System Design SSOT",
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
      { icon: 'github', link: 'https://github.com/YOUR_ORG/knowledge-repository' }
    ]
  }
})