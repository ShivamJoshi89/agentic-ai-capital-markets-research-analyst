import useCountUp from "../hooks/useCountUp.js";

/** Number that counts up on first render. Renders "N/A" for non-numeric input. */
export default function AnimatedNumber({
  value,
  decimals = 2,
  prefix = "",
  suffix = "",
  className = "",
}) {
  const current = useCountUp(value);

  if (current === null) {
    return <span className={className}>N/A</span>;
  }

  return (
    <span className={className}>
      {prefix}
      {current.toLocaleString("en-US", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })}
      {suffix}
    </span>
  );
}
