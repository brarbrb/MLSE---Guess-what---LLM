import React from 'react';
import './Login.scss';

interface Props {
  title: string;
  data?: any;
}

const Login: React.FC<Props> = ({ title, data }) => {
  return (
    <div className="login-form">
      <h2>{title}</h2>
      {data && <pre>{JSON.stringify(data, null, 2)}</pre>}
    </div>
  );
};

export default Login;
