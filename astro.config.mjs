// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightBlog from 'starlight-blog';

import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  site: 'https://vectorstep.io',
  integrations: [
    starlight({
      title: 'VectorStep',
      description:
        'Webhook-triggered, YAML-configured AI pipeline orchestration with confidence gating you can actually trust.',
      logo: { src: './public/favicon.svg' },
      favicon: '/favicon.svg?v=2',
      customCss: ['./src/styles/global.css'],
      // No social entry while RELEASE_STATE (src/pages/index.astro) is 'preview' —
      // a GitHub icon linking nowhere is worse than no icon. Restore this when
      // RELEASE_STATE flips to 'public':
      // social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/bantex01/VectorStep' }],
      plugins: [
        starlightBlog({
          title: 'Blog',
          metrics: { readingTime: true },
        }),
      ],
      sidebar: [
        {
          label: 'Getting Started',
          items: [
            { autogenerate: { directory: 'docs/getting-started' } },
            { label: 'Tutorials', items: [{ autogenerate: { directory: 'docs/tutorials' } }] },
          ],
        },
        { label: 'Guides', items: [{ autogenerate: { directory: 'docs/guides' } }] },
        { label: 'Concepts', items: [{ autogenerate: { directory: 'docs/concepts' } }] },
        { label: 'Installation', items: [{ autogenerate: { directory: 'docs/installation' } }] },
        { label: 'Pipelines', items: [{ autogenerate: { directory: 'docs/pipelines' } }] },
        { label: 'Sources & Executors', items: [{ autogenerate: { directory: 'docs/integrations' } }] },
        { label: 'UI & Insights', items: [{ autogenerate: { directory: 'docs/ui' } }] },
        { label: 'Gateway', items: [{ autogenerate: { directory: 'docs/gateway' } }] },
        { label: 'Operations', items: [{ autogenerate: { directory: 'docs/operations' } }] },
        { label: 'Troubleshooting', items: [{ autogenerate: { directory: 'docs/troubleshooting' } }] },
        { label: 'Reference', items: [{ autogenerate: { directory: 'docs/reference' } }] },
        { label: 'Design & Internals', items: [{ autogenerate: { directory: 'docs/design' } }] },
        { label: 'About the project', items: [{ autogenerate: { directory: 'docs/about' } }] },
      ],
    }),
  ],

  vite: {
    plugins: [tailwindcss()],
  },
});
