# coss ui integration

The dashboard uses official [coss ui](https://coss.com/ui) registry components built on Base UI. Component source lives locally in `src/components/ui`; dependencies and versions are locked in `package-lock.json`.

Components were installed with the registry CLI. `components.json` declares the `@coss` registry and local import aliases. The neutral token preset is in `src/theme.css`. `src/style.css` supplies the application layout and responsive rules without global button/input/select overrides.

Installed components are Button, Card, Badge, Input, Textarea, Select, Field, Alert, Table, Meter, Separator, Tooltip, Dialog and Skeleton, plus Spinner and ScrollArea dependencies. The installed registry sources are from `apps/ui`, which the upstream [licensing file](https://github.com/cosscom/ui/blob/main/LICENSING.md) identifies as MIT. The original MIT notice and upstream licensing scope are retained in `src/components/ui/LICENSE` and `src/components/ui/UPSTREAM-LICENSING.md`.

`dispatch-ui.tsx` combines these components for application status badges, metric cards, evidence dialogs, section panels and item-driven selects. Form controls use Field/FieldLabel/FieldError. Select items are known before render, expose stable values, and retain Base UI keyboard behavior. Buttons explicitly declare submission behavior. Dialogs use Header/Panel/Footer with ghost close buttons and focus restoration. Static vehicle utilization uses Meter. Body positioning and root isolation support portalled overlays.

The official coss and particle skills are installed in the repository's `.agents/skills` directory. The implementation consulted their styling, form, composition and primitive guides and official select, card and dialog particle examples. No runtime call to coss or an AI provider is required.

The React map loads on demand. React is a separate cacheable vendor chunk. Vite ignores the registry's React Server Component hints because this is a client-only application; other build warnings remain enabled.

The existing API, imported data, independent validation, plan state machine and export schema are unchanged. The six browser checks verify the business flow, responsive screens, native required-field blocking, keyboard Select navigation, dialog focus restoration and outage handling.
