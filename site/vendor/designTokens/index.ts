// Stands in for the site's design tokens, which only set styles. Any token
// reads as "0", so no text the page shows depends on them.
const token: any = new Proxy(function () {}, {
  get: (_target, key) => (key === Symbol.toPrimitive ? () => "0" : token),
  apply: () => token,
});

export const colors = token;
export const spacing = token;
export const typography = token;
