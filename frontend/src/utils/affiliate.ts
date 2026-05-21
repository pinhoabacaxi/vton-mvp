export type AffiliateOptions = {
  sourceUrl?: string | null;
  sourceName?: string | null;
  campaign?: string | null;
};

export function buildAffiliateUrl(options: AffiliateOptions): string | null {
  const { sourceUrl, sourceName, campaign } = options;
  if (!sourceUrl) return null;

  try {
    const url = new URL(sourceUrl);
    const params = url.searchParams;
    params.set('utm_source', 'vton_mvp');
    params.set('utm_medium', 'app');
    params.set('utm_campaign', campaign ?? 'virtual_try_on');
    if (sourceName) params.set('utm_content', sourceName);
    return url.toString();
  } catch {
    return sourceUrl;
  }
}
