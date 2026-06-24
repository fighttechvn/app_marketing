// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightBlog from 'starlight-blog';

// Mounted under /docs/ in the integrated site (serve.py umbrella: / landing,
// /Playground/ tool, /docs/ these docs). Override with SITE_BASE for a different
// host — e.g. SITE_BASE=/app_marketing for GitHub Pages at
// https://fighttechvn.github.io/app_marketing/.
const BASE = process.env.SITE_BASE || '/docs';
// Where the umbrella (landing + playground) lives. '' = origin root (local run.sh);
// '/app_marketing' on GitHub Pages where the whole site sits under the repo path.
const UMBRELLA = (process.env.UMBRELLA_BASE || '').replace(/\/$/, '');

// Astro does NOT prefix root-absolute links authored in Markdown/MDX with `base`.
// Prefix doc-internal links (/guides, /reference, /api…) with the docs base, and
// umbrella links (/, /playground/, /screenshots) with the umbrella base.
function rehypeBaseLinks() {
  const base = BASE.replace(/\/$/, '');
  const isUmbrella = (h) =>
    h === '/' || h === '/playground' || h.startsWith('/playground/') || h.startsWith('/screenshots');
  const visit = (node) => {
    if (node.tagName === 'a' && node.properties && typeof node.properties.href === 'string') {
      const h = node.properties.href;
      if (h.startsWith('/') && !h.startsWith('//') && !/^https?:/.test(h)) {
        if (isUmbrella(h)) {
          if (UMBRELLA) node.properties.href = UMBRELLA + h;     // local: leave at root
        } else if (!h.startsWith(base + '/') && h !== base) {
          node.properties.href = base + h;
        }
      }
    }
    (node.children || []).forEach(visit);
  };
  return (tree) => visit(tree);
}

export default defineConfig({
  site: process.env.SITE_ORIGIN || 'https://fighttechvn.github.io',
  base: BASE,
  markdown: { rehypePlugins: [rehypeBaseLinks] },
  integrations: [
    starlight({
      title: 'App Preview',
      // Top-left title links to the umbrella landing ("/") instead of the docs root.
      components: { SiteTitle: './src/components/SiteTitle.astro' },
      description:
        'Set up and use the store-listing preview tool: sync live store data, ' +
        'review the New→Current diff, and verify your App Store Connect / Google Play keys.',
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/fighttechvn' },
      ],
      // Multi-language. English at the root; untranslated pages fall back to it.
      // Arabic is right-to-left. (Japanese uses the BCP-47 code `ja`.)
      defaultLocale: 'root',
      locales: {
        root: { label: 'English', lang: 'en' },
        vi:   { label: 'Tiếng Việt', lang: 'vi' },
        ko:   { label: '한국어', lang: 'ko' },
        ar:   { label: 'العربية', lang: 'ar', dir: 'rtl' },
        ja:   { label: '日本語', lang: 'ja' },
      },
      plugins: [starlightBlog({
        title: 'Blog',
        authors: {
          fighttech: {
            name: 'FightTech',
            title: 'GoBrain team',
            url: 'https://github.com/fighttechvn',
          },
        },
      })],
      sidebar: [
        { label: 'Guides', items: [{ autogenerate: { directory: 'guides' } }] },
        { label: 'Reference', items: [{ autogenerate: { directory: 'reference' } }] },
        { label: 'API reference (interactive)', link: '/api/' },
      ],
    }),
  ],
});
