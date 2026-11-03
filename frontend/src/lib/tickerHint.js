/**
 * Yahoo knows Indian shares only with their exchange suffix, so RELIANCE
 * typed alone comes back as "No data found for RELIANCE". Testers did exactly
 * that; the error now says what to type instead.
 */
const NOT_FOUND = /^No data found for ([A-Z0-9&-]+)$/;

export function withTickerHint(message) {
  const match = NOT_FOUND.exec(message);
  if (!match) return message;
  return `${message}. Indian shares need .NS on the end, for example ${match[1]}.NS.`;
}
