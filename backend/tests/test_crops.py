"""El catálogo publicado cita EcoCrop y no rellena tolerancia a sequía."""

from app.catalog import load_crops


def test_every_crop_has_a_source_and_copied_maize_numbers() -> None:
    crops = load_crops()
    assert len(crops) == 10
    for crop in crops:
        assert crop.fuente
        assert "EcoCrop" in crop.fuente
        assert isinstance(crop.validado, bool)
        assert crop.tolerancia_sequia is None
    maize = next(crop for crop in crops if crop.id == "maiz")
    assert maize.temp.abs_min == 10
    assert maize.precip_ciclo_mm.opt_min == 600
    assert maize.fertilidad == "alta"
    assert maize.fija_nitrogeno is False
    quinoa = next(crop for crop in crops if crop.id == "quinua")
    assert quinoa.temp.opt_min == 14
    assert quinoa.temp_min_helada == -8
    bean = next(crop for crop in crops if crop.id == "frijol")
    assert bean.fija_nitrogeno is True
    assert bean.familia == "fabaceas"
