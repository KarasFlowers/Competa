import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownContentProps {
  content: string;
  className?: string;
  compact?: boolean;
}

function joinClasses(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

function createMarkdownComponents(compact: boolean) {
  const paragraphClass = compact
    ? "my-2 text-base leading-7 text-gray-700"
    : "my-5 text-lg leading-9 text-gray-700";

  const listClass = compact
    ? "my-2 space-y-2 pl-5 text-base leading-7 text-gray-700"
    : "my-5 space-y-3 pl-6 text-lg leading-9 text-gray-700";

  return {
    h1: ({ children }: { children?: ReactNode }) => (
      <div className="group mb-6 mt-8 first:mt-0">
        <h1 className="text-4xl font-bold text-gray-900 pb-3 border-b-2 border-blue-200 group-first:mt-0">
          {children}
        </h1>
        <div className="h-1 w-16 bg-gradient-to-r from-blue-600 to-blue-400 rounded-full mt-2" />
      </div>
    ),
    h2: ({ children }: { children?: ReactNode }) => (
      <div className="flex items-start gap-3 mt-8 mb-4 first:mt-0 group">
        <div className="w-1.5 h-7 bg-gradient-to-b from-blue-600 to-blue-400 rounded-full mt-0.5 flex-shrink-0" />
        <div className="flex-1">
          <h2 className="text-3xl font-bold text-gray-900 group-hover:text-blue-600 transition-colors">
            {children}
          </h2>
          <div className="h-0.5 w-12 bg-gradient-to-r from-blue-500 to-transparent rounded-full mt-1.5" />
        </div>
      </div>
    ),
    h3: ({ children }: { children?: ReactNode }) => (
      <h3 className="mt-6 mb-3 text-2xl font-semibold text-gray-800 flex items-center gap-2 group first:mt-0">
        <span className="w-2 h-2 rounded-full bg-blue-500 group-hover:bg-blue-600 transition-colors" />
        {children}
      </h3>
    ),
    h4: ({ children }: { children?: ReactNode }) => (
      <h4 className="mt-4 mb-2 text-lg font-semibold text-gray-800 first:mt-0">{children}</h4>
    ),
    p: ({ children }: { children?: ReactNode }) => (
      <p className={paragraphClass}>{children}</p>
    ),
    ul: ({ children }: { children?: ReactNode }) => (
      <ul className={joinClasses("list-disc", listClass)}>{children}</ul>
    ),
    ol: ({ children }: { children?: ReactNode }) => (
      <ol className={joinClasses("list-decimal", listClass)}>{children}</ol>
    ),
    li: ({ children }: { children?: ReactNode }) => (
      <li className="pl-1 marker:text-gray-400">{children}</li>
    ),
    blockquote: ({ children }: { children?: ReactNode }) => (
      <blockquote className="my-5 pl-5 py-4 pr-4 border-l-4 border-blue-400 bg-blue-50/60 rounded-r-xl text-gray-700 italic font-medium">
        {children}
      </blockquote>
    ),
    hr: () => (
      <div className="my-8 flex items-center gap-3">
        <div className="flex-1 h-px bg-gradient-to-r from-gray-200 via-blue-300 to-gray-200" />
        <span className="text-gray-400 text-xs">•</span>
        <div className="flex-1 h-px bg-gradient-to-l from-gray-200 via-blue-300 to-gray-200" />
      </div>
    ),
    a: ({
      href,
      children,
    }: {
      href?: string;
      children?: ReactNode;
    }) => (
      <a
        href={href}
        target={href?.startsWith("http") ? "_blank" : undefined}
        rel={href?.startsWith("http") ? "noopener noreferrer" : undefined}
        className="font-semibold text-blue-600 underline decoration-blue-300 underline-offset-3 hover:text-blue-700 hover:decoration-blue-500 transition-colors duration-150"
      >
        {children}
      </a>
    ),
    table: ({ children }: { children?: ReactNode }) => (
      <div className="my-6 overflow-x-auto rounded-2xl border border-gray-200 shadow-sm">
        <table className="min-w-full border-collapse bg-white text-sm">{children}</table>
      </div>
    ),
    thead: ({ children }: { children?: ReactNode }) => (
      <thead className="bg-gradient-to-r from-gray-50 to-gray-100 text-gray-700 border-b-2 border-gray-300">
        {children}
      </thead>
    ),
    tbody: ({ children }: { children?: ReactNode }) => (
      <tbody className="divide-y divide-gray-100">{children}</tbody>
    ),
    tr: ({ children }: { children?: ReactNode }) => (
      <tr className="hover:bg-blue-50/30 transition-colors duration-150">{children}</tr>
    ),
    th: ({ children }: { children?: ReactNode }) => (
      <th className="px-5 py-3.5 text-left font-bold text-gray-900 uppercase text-xs tracking-wider">
        {children}
      </th>
    ),
    td: ({ children }: { children?: ReactNode }) => (
      <td className="px-5 py-3.5 align-top text-gray-700 font-medium">{children}</td>
    ),
    code: ({
      children,
      className,
    }: {
      children?: ReactNode;
      className?: string;
    }) => {
      const text = String(children ?? "").replace(/\n$/, "");
      const isBlock = className?.includes("language-") || text.includes("\n");

      return isBlock ? (
        <code className="text-base text-gray-100 font-mono">
          {text}
        </code>
      ) : (
        <code className="rounded-md bg-gray-100 px-2.5 py-1.5 text-base text-gray-800 font-mono border border-gray-200">
          {text}
        </code>
      );
    },
    pre: ({ children }: { children?: ReactNode }) => (
      <pre className="my-6 overflow-x-auto rounded-xl bg-gray-900 p-6 shadow-lg border border-gray-800 text-gray-100 text-base leading-relaxed">
        {children}
      </pre>
    ),
    strong: ({ children }: { children?: ReactNode }) => (
      <strong className="font-bold text-gray-900 bg-yellow-100/40 px-1 rounded">
        {children}
      </strong>
    ),
    em: ({ children }: { children?: ReactNode }) => (
      <em className="italic text-blue-600 font-medium not-italic">
        {children}
      </em>
    ),
  };
}

export default function MarkdownContent({
  content,
  className,
  compact = false,
}: MarkdownContentProps) {
  return (
    <div className={joinClasses("max-w-none break-words", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={createMarkdownComponents(compact)}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
