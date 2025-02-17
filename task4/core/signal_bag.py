from numba import jit, njit, prange
from numba.experimental import jitclass
import numpy as np
from scipy.optimize import minimize
# from core import weights
from core import weights as weights
from core.req_arrays import *
from core.stacking_analysis import wall_nu
import multiprocessing as mul

@jit(nopython=True, fastmath=True)
def hvovec(lon1=0.0, lat1=0.0, lon2=0.0, lat2=0.0, rad=False):

    '''
    Parameters
    ----------
    lon1 : float
        Longitude of first point.
    lat1 : float
        Latitude of first point.


    lon2 : float
        Longitude of second point.
    lat2 : float
        Latitude of second point.

    rad : Boolean, optional
        (default) False -> Angle is returned in Degrees
        True -> Angle is returned in radians
    

    Returns
    -------
    float
        Returns the haversine angle between two vectors given their latitude and longitude
    

    Warning
    -------
        This function assumes the input to be in degrees and of equal length\n
        or one of the input pairs to be a single value and the other pair to be an array
    '''

    #Convert decimal degrees to Radians:
    lon1 = np.deg2rad(lon1)
    lat1 = np.deg2rad(lat1)
    lon2 = np.deg2rad(lon2)
    lat2 = np.deg2rad(lat2)

    #Implementing Haversine Formula: 
    dlon = np.subtract(lon2, lon1)
    
    a = np.add(np.multiply(np.sin(lat1), np.sin(lat2)), np.multiply(np.multiply(np.cos(lat1), np.cos(lat2)), np.cos(dlon)))

    if rad == True:
        return np.arccos(a)
    else:
        return np.abs(np.arccos(a)/deg2rad_var)



@jit(nopython=True, fastmath=True)
def S_ij(nu): 

    '''
    Parameters
    ----------
    nu : int
        Index of the neutrino in the sample
        
    
    Returns
    -------
        Returns the signal PDF for the {psrno}th pulsar and nuind_inp neutrino
    '''
    ang2 = hvovec(msra, msdec, icra[nu], icdec[nu], rad=True) ** 2#, icra[nuind], icdec[nuind], rad=True) ** 2
    sg = np.deg2rad(icang[nu]) ** 2
    return np.divide(np.exp(-1 * np.divide(ang2, 2*sg)), (2 * np.pi * sg))

@jit(nopython=True, fastmath=True)
def S_i(nu, all_weights, sum_weights, wall):

    '''
        Parameters
        ----------
        nu : int
            Index of the neutrino in the sample

        Returns
        -------
        Returns the signal PDF for the {nu}th neutrino with all pulsars 
        i.e S_i = wieghted-sum_j S_ij
    '''



    sij = S_ij(nu)
    
    #sleep(1e-8)
    return np.sum(np.multiply(sij, all_weights[wall] / sum_weights[wall]))
    #return np.dot(sij, all_weights[wall] ) / sum_weights[wall]




@jit(nopython=True, fastmath=True)
def Bi_stacked(nu, cone=5):

    '''
    Parameters
    ----------
    nu : int
        Index of the neutrino from IceCube sample
    cone : float
        Cone angle in degrees.
    

    Returns
    -------
    float
        Returns the background PDF for the {nu}th neutrino
    '''

    # count = 0
    count = np.sum(np.abs(np.subtract(icdec, icdec[nu])) <= cone)

    # for i in range(len(icdec)):
    #     if abs(icdec[i] - icdec[nu]) <= cone:
    #         count+=1
    binwidth = (np.sin(np.deg2rad(icdec[nu] + cone)) - np.sin(np.deg2rad(icdec[nu] - cone)))*2*np.pi
    return count/(binwidth * lnu)


# @jitclass
class signals:


    def __init__(self, gamma):
        self.gamma = gamma
        weight_obj =  weights.weights(self.gamma)
        self.all_weights = weight_obj.all_weights
        self.sum_weights = weight_obj.sum_weights


    def compute_signal(self):
        all_weights = self.all_weights
        sum_weights = self.sum_weights
        @jit(nopython=True, cache=True)
        def sigbag_nu(nu):
            '''
                Returns the signal and background PDF for the {nu}th neutrino
            '''
            wall = wall_nu(nu)  #Finding the wall/icecube season in which the nu^th neutrino lies
            return S_i(nu,  all_weights, sum_weights, wall)#,Ns]

        pool = mul.Pool(8, maxtasksperchild=100)
        op_async = pool.map_async(sigbag_nu, range(lnu))
        tmp = op_async.get()
        pool.close()
        pool = []
        op_async = []
        tmp = np.asfarray(tmp)
        self.all_sig = tmp
        return self.all_sig

    def compute_background(self):
        pool = mul.Pool(8, maxtasksperchild=100)
        
        op_async = pool.map_async(Bi_stacked, prange(lnu))
        tmp = op_async.get()
        pool.close()
        pool = []
        op_async = []
        tmp = np.asfarray(tmp)
        self.all_bag = tmp
        return self.all_bag