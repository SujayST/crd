export const layoutState = {
  categoryListDropdown: true,
  searchDropdown: false,
  navberHamburger: false,
  loginSignupModal: false,
  loginSignupError: false,
  cartModal: false,
  cartProduct: null,
  singleProductDetail: null,
  inCart: null,
  cartTotalCost: null,
  orderSuccess: false,
  loading: false,
  filterListDropdown: false,
  products: null,
  stores: null,
  loading: false,
  sliderImages: [],
  blogsData: null,
  storeData: null,
};

export const layoutReducer = (state, action) => {
  switch (action.type) {
    case "categoryListDropdown":
      return {
        ...state,
        categoryListDropdown: action.payload,
        filterListDropdown: false,
        searchDropdown: false,
      };
    case "searchDropdown":
      return {
        ...state,
        categoryListDropdown: false,
        filterListDropdown: false,
        searchDropdown: action.payload,
      };
    case "filterListDropdown":
      return {
        ...state,
        categoryListDropdown: false,
        filterListDropdown: action.payload,
        searchDropdown: false,
      };
    case "searchDropdown-4t":
      return {
        ...state,
        searchDropdown: action.payload,
      };
    case "setProducts":
      return {
        ...state,
        products: action.payload,
      };
    case "setStores":
      return {
        ...state,
        stores: action.payload,
      };
    case "blogsData":
      return {
        ...state,
        blogsData: action.payload,
      }
    case "searchHandleInReducer":
      return {
        ...state,
        products:
          action.productArray &&
          action.productArray.filter((item) => {
            if (
              item.pName.toUpperCase().indexOf(action.payload.toUpperCase()) !==
              -1
            ) {
              return item;
            }
            return null;
          }),
      };
    case "categoryListDropdown":
      return {
        ...state,
        categoryListDropdown: action.payload,
        filterListDropdown: false,
        searchDropdown: false,
      };
    case "hamburgerToggle":
      return {
        ...state,
        navberHamburger: action.payload,
      };
    case "loginSignupModalToggle":
      return {
        ...state,
        loginSignupModal: action.payload,
      };
    case "cartModalToggle":
      return {
        ...state,
        cartModal: action.payload,
      };
    case "cartProduct":
      return {
        ...state,
        cartProduct: action.payload,
      };
    case "singleProductDetail":
      return {
        ...state,
        singleProductDetail: action.payload,
      };
    case "inCart":
      return {
        ...state,
        inCart: action.payload,
      };
    case "cartTotalCost":
      return {
        ...state,
        cartTotalCost: action.payload,
      };
    case "loginSignupError":
      return {
        ...state,
        loginSignupError: action.payload,
      };
    case "orderSuccess":
      return {
        ...state,
        orderSuccess: action.payload,
      };
    case "sliderImages":
      return {
        ...state,
        sliderImages: action.payload,
      };

    case "loading":
      return {
        ...state,
        loading: action.payload,
      };
    default:
      return state;
  }
};
