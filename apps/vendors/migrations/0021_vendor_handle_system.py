# Generated migration for vendor handle system

from django.db import migrations, models
import django.utils.text


def generate_handles_for_existing_vendors(apps, schema_editor):
    """
    Generate unique handles for all existing vendors that don't have one.
    This ensures backward compatibility.
    """
    Vendor = apps.get_model('vendors', 'Vendor')
    
    for vendor in Vendor.objects.filter(handle__isnull=True):
        # Generate base slug from business name
        base_slug = django.utils.text.slugify(vendor.business_name)
        
        if not base_slug:
            base_slug = f"vendor-{vendor.id}"
        
        # Truncate to leave room for suffix
        base_slug = base_slug[:46]
        
        handle = base_slug
        counter = 1
        
        # Find unique handle
        while Vendor.objects.filter(handle=handle).exists():
            handle = f"{base_slug}-{counter}"
            counter += 1
        
        vendor.handle = handle
        vendor.save(update_fields=['handle'])
        print(f"Generated handle '{handle}' for vendor {vendor.id} ({vendor.business_name})")


def reverse_migration(apps, schema_editor):
    """
    Reverse migration - set all handles to None
    """
    Vendor = apps.get_model('vendors', 'Vendor')
    Vendor.objects.all().update(handle=None)


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0020_vendor_handle'),  # Latest migration
    ]

    operations = [
        # Step 1: Alter field from CharField to SlugField
        migrations.AlterField(
            model_name='vendor',
            name='handle',
            field=models.SlugField(
                blank=True,
                db_index=True,
                help_text='Permanent URL handle for vendor portfolio. Auto-generated on onboarding, never auto-updates.',
                max_length=50,
                null=True,
                unique=True
            ),
        ),
        
        # Step 2: Add Meta indexes
        migrations.AlterModelOptions(
            name='vendor',
            options={},
        ),
        
        # Step 3: Add database indexes
        migrations.AddIndex(
            model_name='vendor',
            index=models.Index(fields=['business_email'], name='vendors_ven_busines_idx'),
        ),
        migrations.AddIndex(
            model_name='vendor',
            index=models.Index(fields=['business_phone'], name='vendors_ven_busines_phone_idx'),
        ),
        migrations.AddIndex(
            model_name='vendor',
            index=models.Index(fields=['handle'], name='vendors_ven_handle_idx'),
        ),
        migrations.AddIndex(
            model_name='vendor',
            index=models.Index(fields=['is_active', 'is_verified'], name='vendors_ven_is_acti_idx'),
        ),
        migrations.AddIndex(
            model_name='vendor',
            index=models.Index(fields=['created_at'], name='vendors_ven_created_idx'),
        ),
        
        # Step 4: Generate handles for existing vendors
        migrations.RunPython(
            generate_handles_for_existing_vendors,
            reverse_migration
        ),
    ]
