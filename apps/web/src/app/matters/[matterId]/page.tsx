import { MatterWorkbench } from "@/components/MatterWorkbench";

export default async function MatterPage({
  params
}: {
  params: Promise<{ matterId: string }>;
}) {
  const { matterId } = await params;
  return <MatterWorkbench matterId={matterId} />;
}
