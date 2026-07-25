import Image from "next/image";

import { classNames } from "@/lib/format";

export function MoviePoster({
  title,
  src,
  priority = false,
  className,
}: {
  title: string;
  src: string | null;
  priority?: boolean;
  className?: string;
}) {
  const fallbackTitleSize =
    title.length > 14 ? "text-sm leading-5" : "text-xl leading-6";

  return (
    <div
      className={classNames(
        "relative aspect-[2/3] overflow-hidden bg-[#171719]",
        className,
      )}
    >
      {src ? (
        <Image
          src={src}
          alt={`${title} theatrical key art`}
          fill
          priority={priority}
          sizes="(min-width: 1280px) 240px, (min-width: 768px) 22vw, 42vw"
          className="object-cover"
        />
      ) : (
        <div className="surface-grid absolute inset-0 flex items-end p-3">
          <div className="min-w-0">
            <span className="mb-3 block h-1 w-8 bg-[var(--signal)]" />
            <p
              className={classNames(
                "font-editorial break-words text-white",
                fallbackTitleSize,
              )}
            >
              {title}
            </p>
            <p className="mt-2 text-[9px] font-bold text-[var(--muted)] uppercase">
              Artwork pending source sync
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
