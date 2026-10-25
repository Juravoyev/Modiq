/** Modiq logosi: izometrik kub. */
export function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <path d="M32 4 58 19 32 34 6 19z" fill="#0FA374" />
      <path d="M32 34v26L6 45V19z" fill="#087F5B" />
      <path d="M32 34 58 19v26L32 60z" fill="#0B5A41" />
    </svg>
  );
}
