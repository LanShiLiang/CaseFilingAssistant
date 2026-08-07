import { MatterWorkbench } from "@/features/matter-workbench/MatterWorkbench";

export default async function MatterPage({
  params
}: {
  params: Promise<{ matterId: string }>;
}) {
  const { matterId } = await params;
  return <MatterWorkbench matterId={matterId} />;
}
