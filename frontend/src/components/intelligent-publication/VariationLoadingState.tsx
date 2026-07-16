import { motion } from "framer-motion";

const nodes = [
  { cx: 25, cy: 8 },
  { cx: 27, cy: 16 },
  { cx: 25, cy: 24 },
];

export function VariationLoadingState({ accountCount }: { accountCount: number }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-10">
      <svg viewBox="0 0 32 32" className="h-14 w-14 text-primary">
        <motion.circle
          cx="7"
          cy="16"
          r="3.5"
          fill="currentColor"
          animate={{ scale: [1, 1.15, 1] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
        />
        {nodes.map((node, index) => (
          <motion.path
            key={`${node.cx}-${node.cy}`}
            d={`M9 16 L${node.cx} ${node.cy}`}
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            initial={{ pathLength: 0, opacity: 0.3 }}
            animate={{ pathLength: [0, 1, 1, 0], opacity: [0.3, 1, 1, 0.3] }}
            transition={{
              duration: 1.8,
              repeat: Infinity,
              delay: index * 0.15,
              ease: "easeInOut",
            }}
          />
        ))}
        {nodes.map((node, index) => (
          <motion.circle
            key={`dot-${node.cx}-${node.cy}`}
            cx={node.cx}
            cy={node.cy}
            r="2.2"
            fill="currentColor"
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.8, repeat: Infinity, delay: index * 0.15 }}
          />
        ))}
      </svg>
      <div className="space-y-1 text-center">
        <p className="text-sm font-medium text-foreground">Gerando variações com IA…</p>
        <p className="text-xs text-muted-foreground">
          Criando {accountCount} {accountCount === 1 ? "versão" : "versões"} preservando links,
          hashtags e menções.
        </p>
      </div>
    </div>
  );
}
