export default function MeterLogo({ size = 34, glowing = true, className = "", style = {} }) {
  return (
    <img
      src="/logo.png"
      alt="MeterGuard AI Logo"
      width={size}
      height={size}
      className={`meter-logo ${className}`.trim()}
      style={{
        width: `${size}px`,
        height: `${size}px`,
        objectFit: "contain",
        borderRadius: "6px",
        filter: glowing ? "drop-shadow(0 0 6px rgba(34, 197, 94, 0.45))" : "none",
        flexShrink: 0,
        display: "block",
        ...style,
      }}
    />
  );
}
