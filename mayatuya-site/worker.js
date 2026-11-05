// Maya Tuya — thin Worker in front of the static assets (docs/).
// 1. www.mayatuya.com -> https://mayatuya.com (301, path and query kept).
// 2. Any host other than the apex (new.mayatuya.com, *.workers.dev previews) is served with
//    X-Robots-Tag: noindex so only mayatuya.com is indexed. Pages already canonical to the apex.
// Everything else (redirects, headers, 404, trailing slashes) is handled by the static-assets layer.
const APEX = 'mayatuya.com';

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.hostname === 'www.' + APEX) {
      url.protocol = 'https:';
      url.hostname = APEX;
      url.port = '';
      return Response.redirect(url.toString(), 301);
    }
    const res = await env.ASSETS.fetch(request);
    if (url.hostname === APEX) return res;
    const out = new Response(res.body, res);
    out.headers.set('X-Robots-Tag', 'noindex, nofollow');
    return out;
  },
};
