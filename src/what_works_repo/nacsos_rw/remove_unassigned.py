from nacsos_data.db import get_engine
from nacsos_data.db.schemas import Assignment, Import
from sqlalchemy import select

IMPORT_ID = "ed13c207-bced-4787-b800-0bcfd0320b89"
SCHEME_ID = "81f7d9d5-1f78-4039-80da-6fd2d3a46733"


def main():
    db_engine = get_engine("config/.env")

    with db_engine.session() as session:
        import_obj = session.execute(
            select(Import).filter(Import.import_id == IMPORT_ID)
        ).scalar_one()

        import_items = import_obj.items
        print(f"Total items in import: {len(import_items)}")

        # Get assigned items
        assignments = (
            session.execute(
                select(Assignment).filter(Assignment.annotation_scheme_id == SCHEME_ID)
            )
            .scalars()
            .all()
        )

        assigned_ids = {assignment.item_id for assignment in assignments}
        unassigned = [item for item in import_items if item.item_id not in assigned_ids]

        print(f"Items assigned in scheme: {len(assigned_ids)}")
        print(f"Unassigned items: {len(unassigned)}")

        response = input("Delete these items? (y/n): ")
        if response.lower() == "y":
            for item in unassigned:
                import_obj.items.remove(item)

            session.commit()

            new_count = len(import_obj.items)
            print(f"Deleted {len(unassigned)} items")
            print(f"Import now contains {new_count} items")
        else:
            print("Cancelled")


if __name__ == "__main__":
    main()
