type props = {
  message: string;
};

export const InfoBanner: React.FC<props> = ({ message }) => (
  <div className="flex">
    <div className="bg-blue-100 p-5 w-full  border-l-4 border-blue-500">
      <div className="flex space-x-3">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          className="flex-none fill-current text-blue-500 h-4 w-4"
        >
          <path d="M12 0c-6.627 0-12 5.373-12 12s5.373 12 12 12 12-5.373 12-12-5.373-12-12-12zm-.001 5.75c.69 0 1.251.56 1.251 1.25s-.561 1.25-1.251 1.25-1.249-.56-1.249-1.25.559-1.25 1.249-1.25zm2.001 12.25h-4v-1c.484-.179 1-.201 1-.735v-4.467c0-.534-.516-.618-1-.797v-1h3v6.265c0 .535.517.558 1 .735v.999z" />
        </svg>
        <div className="flex-1 leading-tight text-sm text-blue-700">
          {message}
        </div>
      </div>
    </div>
  </div>
);
