/**
 * Sparsa Homeo Care brand mark. Single source of truth.
 * Falls back to nothing if image is missing — the wrapping markup keeps the layout.
 */
export default function Logo({ size = 36, className = "" }) {
  return (
    <img
      src="/logo.png"
      alt="Sparsa Homeo Care"
      width={size}
      height={size}
      className={`object-contain ${className}`}
      data-testid="brand-logo"
    />
  );
}
