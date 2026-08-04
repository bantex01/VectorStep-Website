// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  site: 'https://quorate.io',
  integrations: [
    starlight({
      title: 'Quorate',
      description:
        'Webhook-triggered, YAML-configured AI pipeline orchestration with confidence gating you can actually trust.',
      logo: { src: './public/favicon.svg' },
      favicon: '/favicon.svg?v=2',
      customCss: ['./src/styles/global.css'],
      social: [
        // TODO: point at the real GitHub org/repo once public
        { icon: 'github', label: 'GitHub', href: 'https://github.com' },
      ],
      sidebar: [
        { label: 'Getting Started', items: [{ autogenerate: { directory: 'docs/getting-started' } }] },
        { label: 'Concepts', items: [{ autogenerate: { directory: 'docs/concepts' } }] },
        { label: 'Pipelines', items: [{ autogenerate: { directory: 'docs/pipelines' } }] },
        { label: 'Sources & Executors', items: [{ autogenerate: { directory: 'docs/integrations' } }] },
        { label: 'UI & Insights', items: [{ autogenerate: { directory: 'docs/ui' } }] },
        { label: 'Gateway', items: [{ autogenerate: { directory: 'docs/gateway' } }] },
        { label: 'Operations', items: [{ autogenerate: { directory: 'docs/operations' } }] },
        { label: 'Reference', items: [{ autogenerate: { directory: 'docs/reference' } }] },
        { label: 'Design', items: [{ autogenerate: { directory: 'docs/design' } }] },
      ],
    }),
  ],

  vite: {
    plugins: [tailwindcss()],
  },
});
