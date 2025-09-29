import React from 'react';
import MenuSection from "./MenuSection";
import ProfileSection from "./ProfileSection";
import './HomeArticle.scss';

interface Props {
  title: string;
  data?: any;
}

const HomeArticle: React.FC<Props> = ({title, data}) => {
  return (
    <article className="home">
      <MenuSection/>
      <ProfileSection/>
    </article>
  );
};

export default HomeArticle;
