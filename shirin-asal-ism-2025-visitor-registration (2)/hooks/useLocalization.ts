
import { useLanguage } from '../context/LanguageContext';

export const useLocalization = () => {
    const { t } = useLanguage();
    return { t };
};
