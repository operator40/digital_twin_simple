from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Asset, DataCollectorSyncState
from .schemas import (
    AssetMappingBatchIn,
    AssetMappingBatchResult,
    AssetMappingItemResult,
)


async def apply_asset_mappings(
    session: AsyncSession,
    batch: AssetMappingBatchIn,
) -> AssetMappingBatchResult:
    """Create missing mappings and report existing or conflicting pairs."""

    results: list[AssetMappingItemResult] = []
    mapping_changed = False

    for mapping in batch.mappings:
        cmms_asset = None
        if mapping.cmms_asset_id is not None:
            cmms_asset = await session.scalar(
                select(Asset).where(
                    Asset.cmms_asset_id == mapping.cmms_asset_id
                )
            )

        dc_asset = None
        if mapping.dc_asset_id is not None:
            dc_asset = await session.scalar(
                select(Asset).where(Asset.dc_asset_id == mapping.dc_asset_id)
            )

        if (
            cmms_asset is not None
            and dc_asset is not None
            and cmms_asset.asset_id != dc_asset.asset_id
        ):
            results.append(
                AssetMappingItemResult(
                    **mapping.model_dump(),
                    status="conflict",
                    reason=(
                        "The CMMS and DC identifiers are already assigned "
                        "to different assets"
                    ),
                )
            )
            continue

        asset = cmms_asset or dc_asset

        if asset is None:
            asset = Asset(
                cmms_asset_id=mapping.cmms_asset_id,
                dc_asset_id=mapping.dc_asset_id,
            )
            session.add(asset)
            await session.flush()
            item_status = "created"
            mapping_changed = True
        elif (
            mapping.cmms_asset_id is not None
            and asset.cmms_asset_id not in (None, mapping.cmms_asset_id)
        ) or (
            mapping.dc_asset_id is not None
            and asset.dc_asset_id not in (None, mapping.dc_asset_id)
        ):
            results.append(
                AssetMappingItemResult(
                    **mapping.model_dump(),
                    status="conflict",
                    asset_id=int(asset.asset_id),
                    reason="One identifier is already mapped to another value",
                )
            )
            continue
        else:
            item_changed = False
            if (
                mapping.cmms_asset_id is not None
                and asset.cmms_asset_id is None
            ):
                asset.cmms_asset_id = mapping.cmms_asset_id
                item_changed = True
            if mapping.dc_asset_id is not None and asset.dc_asset_id is None:
                asset.dc_asset_id = mapping.dc_asset_id
                item_changed = True

            if item_changed:
                await session.flush()
                item_status = "updated"
                mapping_changed = True
            else:
                item_status = "unchanged"

        results.append(
            AssetMappingItemResult(
                **mapping.model_dump(),
                status=item_status,
                asset_id=int(asset.asset_id),
            )
        )

    if mapping_changed:
        dc_state = await session.get(DataCollectorSyncState, "silverfrog_dc")
        if dc_state is not None:
            dc_state.last_metrics_sync_at = None

    await session.commit()

    return AssetMappingBatchResult(
        created=sum(item.status == "created" for item in results),
        updated=sum(item.status == "updated" for item in results),
        unchanged=sum(item.status == "unchanged" for item in results),
        conflicts=sum(item.status == "conflict" for item in results),
        results=results,
    )
