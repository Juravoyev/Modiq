import shutil
import tempfile
from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.accounts.models import Membership
from apps.catalog.models import Product
from apps.common.testing import client_for, make_business, make_member, make_variant

MEDIA = tempfile.mkdtemp(prefix="modiq-test-media-")


def _upload(width=3000, height=2000, fmt="JPEG", name="photo.jpg"):
    buf = BytesIO()
    Image.new("RGB", (width, height), (200, 30, 30)).save(buf, format=fmt)
    return SimpleUploadedFile(name, buf.getvalue(), content_type=f"image/{fmt.lower()}")


@override_settings(MEDIA_ROOT=MEDIA)
class ProductImageTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.business, (self.branch,), self.owner, _ = make_business()
        self.c = client_for(self.owner)
        self.product = make_variant(self.business).product
        self.url = f"/api/catalog/products/{self.product.id}/image/"

    def _file(self):
        self.product.refresh_from_db()
        return Path(MEDIA) / self.product.image.name

    def test_upload_is_resized_and_converted_to_webp(self):
        with self.captureOnCommitCallbacks(execute=True):
            r = self.c.post(self.url, {"image": _upload()}, format="multipart")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(r.data["image"].startswith("/media/products/"))
        self.assertTrue(r.data["image"].endswith(".webp"))
        with Image.open(self._file()) as img:
            self.assertEqual(img.format, "WEBP")
            self.assertEqual(img.size, (1200, 800))

    def test_variant_list_includes_product_image_for_pos(self):
        self.c.post(self.url, {"image": _upload()}, format="multipart")
        variant = self.c.get("/api/catalog/variants/").data["results"][0]
        self.assertTrue(variant["product_image"].endswith(".webp"))

    def test_replacing_image_deletes_old_file(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.c.post(self.url, {"image": _upload()}, format="multipart")
        old = self._file()
        with self.captureOnCommitCallbacks(execute=True):
            self.c.post(self.url, {"image": _upload(fmt="PNG", name="b.png")}, format="multipart")
        self.assertFalse(old.exists())
        self.assertTrue(self._file().exists())

    def test_remove_image_deletes_file(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.c.post(self.url, {"image": _upload()}, format="multipart")
        path = self._file()
        with self.captureOnCommitCallbacks(execute=True):
            r = self.c.delete(self.url)
        self.assertIsNone(r.data["image"])
        self.assertFalse(path.exists())

    def test_hard_deleting_product_deletes_image_file(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.c.post(self.url, {"image": _upload()}, format="multipart")
        path = self._file()
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.c.delete(f"/api/catalog/products/{self.product.id}/").status_code, 204)
        self.assertFalse(path.exists())

    def test_non_image_file_rejected(self):
        fake = SimpleUploadedFile("virus.jpg", b"not an image", content_type="image/jpeg")
        r = self.c.post(self.url, {"image": fake}, format="multipart")
        self.assertEqual(r.status_code, 400)
        self.assertIn("image", r.data)
        self.product.refresh_from_db()
        self.assertFalse(self.product.image)

    def test_cashier_cannot_upload(self):
        cashier, _ = make_member(self.business, Membership.Role.CASHIER, [self.branch])
        r = client_for(cashier).post(self.url, {"image": _upload()}, format="multipart")
        self.assertEqual(r.status_code, 403)

    def test_other_business_cannot_upload(self):
        _, _, stranger, _ = make_business()
        r = client_for(stranger).post(self.url, {"image": _upload()}, format="multipart")
        self.assertEqual(r.status_code, 404)
        self.assertFalse(Product.objects.get(pk=self.product.pk).image)
