'''
This code presents an approach for implementing the gravitational field
produced by a polygonal prism by using the analytical formulas of
Plouff (1976). It also makes use of the modified arctangent function proposed
by Fukushima (2020, eq. 72).

References
* Plouff, D. , 1976, Gravity and magnetic fields of polygonal prisms and
    applications to magnetic terrain corrections, Geophysics,
    41(4), 727-741. https://doi.org/10.1190/1.1440645

* Fukushima, T. (2020). Speed and accuracy improvements in standard algorithm
    for prismatic gravitational field. Geophysical Journal International,
    222(3), 1898–1908. http://doi.org/10.1093/gji/ggaa240

'''

import numpy as np
from numba import njit

#: The gravitational constant in m^3 kg^{-1} s^{-1}
GRAVITATIONAL_CONST = 0.00000000006673

@njit
def safe_atan2(y, x):
    """
    Principal value of the arctangent expressed as a two variable function

    This modification has to be made to the arctangent function so the
    gravitational field of the prism satisfies the Poisson's equation.
    Therefore, it guarantees that the fields satisfies the symmetry properties
    of the prism. This modified function has been defined according to
    Fukushima (2020, eq. 72).
    """
    if x != 0:
        result = np.arctan(y / x)
    else:
        if y > 0:
            result = np.pi / 2
        elif y < 0:
            result = -np.pi / 2
        else:
            result = 0
    return result

@njit
def safe_log(x):
    """
    Modified log to return 0 for log(0).
    The limits in the formula terms tend to 0.
    """
    if np.abs(x) < 1e-10:
        result = 0
    else:
        result = np.log(x)
    return result


def gravitational(coordinates,polygons,thicknesses,density,field):
    """
    Computing the gravitational field generated by a polygonal prism.
    """

    kernels = {
        "gz": kernel_gz
    }

    # Checking input field
    if field not in kernels:
        raise ValueError(
            "Gravitational field {} not recognized".format(field)
        )

    # Checking input parameters
    if coordinates.ndim != 2:
        raise ValueError(
            "coordinates ndim ({}) ".format(coordinates.ndim)
            + "not equal to 2"
        )
    if coordinates.shape[0] != 3:
        raise ValueError(
            "Number of lines in coordinates ({}) ".format(coordinates.shape[0])
            + "not equal to 3"
        )
    
    if type(polygons) != list:
        raise ValueError(
            "Input polygons ({}) not recognized".format(a)
        )
    
    if thicknesses.ndim != 2:
        raise ValueError(
            "Thicknesses ndim ({}) ".format(thicknesses.ndim)
            + "not equal to 2"
        )

    if thicknesses.shape[1] != 2:
        raise ValueError(
            "Number of columns in thicknesses ({})".format(thicknesses.shape[1])
            + "not equal to 2"
        )

    if thicknesses.shape[0] != len(polygons):
        raise ValueError(
            "Number of polygons ({}) and thicknesses ({}) are different".format(len(polygons),thicknesses.shape[0])
        )
    
    if density.ndim != 1:
        raise ValueError(
            "density ndim ({}) ".format(density.ndim)
            + "not equal to 1"
        )

    if thicknesses.shape[0] != density.shape[0]:
        raise ValueError(
            "Number of polygons ({}) and density ({}) are different".format(thicknesses.shape[0],density.shape[0])
        )

    # Create the array to store the result
    result = np.zeros(coordinates[0].size, dtype="float64")

    # Compute gravitational field
    jit_gravitational(coordinates,polygons,thicknesses,density,kernels[field],result)
    result *= GRAVITATIONAL_CONST
    # Convert from m/s^2 to mGal
    if field in ["gz"]:
        result *= 1e5
    return result

@njit
def jit_gravitational(coordinates,polygons,thicknesses,density,kernel,out):
    """
    Compute gravitational field at the observation points
    """
    # Iterate over coordinates
    for l in range(coordinates[0].size):
        # Iterate over polygons
        for m in range(len(polygons)):
            # Iterate over polygons vertices
            nverts = polygons[m].size//2
            for i in range(nverts-1):
                Y1 = polygons[m][0,i] - coordinates[0,l]
                Y2 = polygons[m][0,i+1] - coordinates[0,l]
                X1 = polygons[m][1,i] - coordinates[1,l]
                X2 = polygons[m][1,i+1] - coordinates[1,l]
                Z1 = thicknesses[m,0] - coordinates[2,l]
                Z2 = thicknesses[m,1] - coordinates[2,l]
                out[l] += (density[m] * kernel(Y1,Y2,X1,X2,Z1,Z2))


@njit
def kernel_gz(Y1,Y2,X1,X2,Z1,Z2):
    """
    Kernel for downward component of gravitational acceleration of a polygonal prism
    """
    dummy = 1e-10
    Z1_sqr = Z1**2
    Z2_sqr = Z2**2
    p = X1*Y2 - X2*Y1
    p_sqr = p**2
    Q1 = (Y2 - Y1)*Y1 + (X2 - X1)*X1
    Q2 = (Y2 - Y1)*Y2 + (X2 - X1)*X2
    A1 = X1**2 + Y1**2
    A2 = X2**2 + Y2**2
    R11 = np.sqrt(A1 + Z1_sqr)
    R12 = np.sqrt(A2 + Z1_sqr)
    R21 = np.sqrt(A1 + Z2_sqr)
    R22 = np.sqrt(A2 + Z2_sqr)
    A1 = np.sqrt(A1)
    A2 = np.sqrt(A2)
    B1 = np.sqrt(Q1**2 + p_sqr)
    B2 = np.sqrt(Q2**2 + p_sqr)
    E11 = R11*B1
    E12 = R12*B2
    E21 = R21*B1
    E22 = R22*B2
    C1 = Q1*A1
    C2 = Q2*A2
    
    T1 = (Z2 - Z1)*(safe_atan2(Q2,p) - safe_atan2(Q1,p))
    T2 = Z2*(safe_atan2(Z2*Q1, R21*p) - safe_atan2(Z2*Q2,R22*p))
    T3 = Z1*(safe_atan2(Z1*Q2, R12*p) - safe_atan2(Z1*Q1,R11*p))
    
    T4 = (0.5*p*A1/B1)*safe_log(
        ((E11 - C1)*(E21 + C1))/((E11 + C1)*(E21 - C1)))
    T5 = (0.5*p*A2/B2)*safe_log(
        ((E22 - C2)*(E12 + C2))/((E22 + C2)*(E12 - C2)))
    kernel = T1 + T2 + T3 + T4 + T5
    return kernel
    
    