use pyo3::prelude::*;

fn sum_of_squares_impl(values: &[f64]) -> f64 {
    values.iter().map(|value| value * value).sum()
}

fn plane_distances_impl(points: &[[f64; 3]], normal: [f64; 3], offset: f64) -> Vec<f64> {
    points
        .iter()
        .map(|point| point[0] * normal[0] + point[1] * normal[1] + point[2] * normal[2] - offset)
        .collect()
}

#[pyfunction]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

#[pyfunction]
fn sum_of_squares(py: Python<'_>, values: Vec<f64>) -> f64 {
    py.detach(move || sum_of_squares_impl(&values))
}

#[pyfunction]
fn plane_distances(points: Vec<[f64; 3]>, normal: [f64; 3], offset: f64) -> Vec<f64> {
    plane_distances_impl(&points, normal, offset)
}

#[pymodule]
fn raumlot_native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(version, module)?)?;
    module.add_function(wrap_pyfunction!(sum_of_squares, module)?)?;
    module.add_function(wrap_pyfunction!(plane_distances, module)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{plane_distances_impl, sum_of_squares_impl};

    #[test]
    fn sums_squares() {
        assert_eq!(sum_of_squares_impl(&[1.0, 2.0, 3.0]), 14.0);
        assert_eq!(sum_of_squares_impl(&[]), 0.0);
    }

    #[test]
    fn calculates_signed_plane_distances() {
        let points = [[0.0, 0.0, 0.0], [1.5, -2.0, 1.0], [0.0, 4.0, 3.25]];

        assert_eq!(
            plane_distances_impl(&points, [0.0, 0.0, 1.0], 1.0),
            vec![-1.0, 0.0, 2.25]
        );
    }
}
